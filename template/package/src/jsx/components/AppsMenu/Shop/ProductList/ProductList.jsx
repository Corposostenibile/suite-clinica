import React, { Fragment, useState } from "react";
import { Link } from "react-router-dom";
import { Modal, Col, Row } from "react-bootstrap";

import PageTitle from "../../../../layouts/PageTitle";

// images
import avatar1 from "../../../../..//images/avatar/1.jpg";
import product2 from "../../../../../images/product/2.jpg";
import product3 from "../../../../../images/product/3.jpg";
import product4 from "../../../../../images/product/4.jpg";
import product5 from "../../../../../images/product/5.jpg";
import product6 from "../../../../../images/product/6.jpg";
import product7 from "../../../../../images/product/7.jpg";

const productItem = [
  { image: product2, title:'Slip Dress', price:'320', brand:'Lee'},
  { image: product3, title:'Smock Dress', price:'325', brand:'Levis'},
  { image: product4, title:'Ballgown', price:'375', brand:'Lee'},
  { image: product5, title:'Silhouette Dress', price:'299', brand:'Nike'},
  { image: product6, title:'Tea Length Dress', price:'405', brand:'Puma'},
  { image: product7, title:'Cocktail Dress', price:'280', brand:'Mufti'},
];

const ProductList = () => {
  const [reviewModal, setReviewModal] = useState(false);
  return (
    <Fragment>
      <PageTitle activeMenu="Product List" motherMenu="Shop" />
      <Row>
        {productItem.map((data, ind)=>(
            <Col lg={12} xl={6} xxl={4} key={ind}>
              <div className="card">
                <div className="card-body">
                  <div className="row m-b-30">
                    <div className="col-md-5 col-xxl-12">
                      <div className="new-arrival-product mb-4 mb-xxl-4 mb-md-0">
                        <div className="new-arrivals-img-contnent">
                          <img className="img-fluid" src={data.image} alt="" />
                        </div>
                      </div>
                    </div>
                    <div className="col-md-7 col-xxl-12">
                      <div className="new-arrival-content position-relative">
                        <h4>{data.title}</h4>
                        <p className="price style-1">${data.price}.00</p>                   
                        <p>
                          Availability:{" "}
                          <span className="item">
                            {" "}
                            In stock{" "}
                            <i className="fa fa-check-circle text-success" />
                          </span>
                        </p>
                        <p>
                          Product code: <span className="item">0405689</span>{" "}
                        </p>
                        <p>
                          Brand: <span className="item">{data.brand}</span>
                        </p>
                        <p className="text-content">
                          There are many variations of passages of Lorem Ipsum available, 
                          but the majority have suffered alteration in some form, by injected humour, 
                          or randomised words which don't look even slightly believable. 
                          If you are going to use a passage of Lorem Ipsum.
                        </p>
                        <div className="comment-review star-rating text-end">
                          <ul>
                            {" "}
                            <li><i className="fa fa-star" /></li>{" "}
                            <li><i className="fa fa-star" /></li>{" "}
                            <li><i className="fa fa-star" /></li>{" "}
                            <li><i className="fa-solid fa-star-half-stroke" /></li>{" "}
                            <li><i className="fa-solid fa-star-half-stroke" /></li>
                          </ul>
                          <span className="review-text">(34 reviews) / </span>
                          <Link
                            className="product-review"
                            to="#"
                            
                            onClick={() => setReviewModal(true)}
                            data-target="#reviewModal"
                          >
                            Write a review?
                          </Link>
                          
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </Col>
        ))}       
        {/* review */}
        <Modal show={reviewModal} className="modal fade" id="reviewModal" centered> 
          <>
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Review</h5>
                <button
                  type="button"
                  className="btn-close"                  
                  onClick={() => setReviewModal(false)}
                >
                  
                </button>
              </div>
              <div className="modal-body">
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    setReviewModal(false);
                  }}
                >
                  <div className="text-center mb-4">
                    <img
                      className="img-fluid rounded"
                      width={78}
                      src={avatar1}
                      alt="DexignZone"
                    />
                  </div>
                  <div className="mb-3">
                    <div className="rating-widget mb-4 text-center">
                      {/* Rating Stars Box */}
                      <div className="rating-stars">
                        <ul
                          id="stars"
                          className="d-flex justify-content-center align-items-center"
                        >
                          <li className="star" title="Poor" data-value={1}>
                            <i className="fa fa-star fa-fw" />
                          </li>
                          <li className="star" title="Fair" data-value={2}>
                            <i className="fa fa-star fa-fw" />
                          </li>
                          <li className="star" title="Good" data-value={3}>
                            <i className="fa fa-star fa-fw" />
                          </li>
                          <li className="star" title="Excellent" data-value={4}>
                            <i className="fa fa-star fa-fw" />
                          </li>
                          <li className="star" title="WOW!!!" data-value={5}>
                            <i className="fa fa-star fa-fw" />
                          </li>
                        </ul>
                      </div>
                    </div>
                  </div>
                  <div className="mb-3">
                    <textarea
                      className="form-control"
                      placeholder="Comment"
                      rows={5}
                      defaultValue={""}
                    />
                  </div>
                  <button className="btn btn-success btn-block">RATE</button>
                </form>
              </div>
            </div>
          </>
        </Modal>
      </Row>
    </Fragment>
  );
};

export default ProductList;
